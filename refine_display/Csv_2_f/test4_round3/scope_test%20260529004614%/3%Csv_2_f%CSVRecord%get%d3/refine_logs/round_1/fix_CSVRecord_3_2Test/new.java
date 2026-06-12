package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_3_2Test {

    @Test
    public void testGet_normalCase() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);
        
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        String result = record.get("header1");
        
        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_nullMapping() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(values, null, null, 1);
        
        Assertions.assertThrows(IllegalStateException.class, () -> {
            record.get("header1");
        });
    }

    @Test
    public void testGet_nonExistentHeader() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        String result = record.get("header2");
        
        Assertions.assertEquals(null, result);
    }

    @Test
    public void testGet_outOfBoundsIndex() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 2); // Out of bounds
        
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertThrows(IllegalArgumentException.class, () -> {
            record.get("header2");
        });
    }

    @Test
    public void testGet_emptyValues() throws Exception {
        String[] values = {"", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        String result = record.get("header1");
        
        Assertions.assertEquals("", result);
    }

    @Test
    public void testGet_invalidHeaderName() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertThrows(IllegalArgumentException.class, () -> {
            record.get("invalidHeader");
        });
    }

    @Test
    public void testGet_nullValue() throws Exception {
        String[] values = {"value1", null, "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);
        
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        String result = record.get("header2");
        
        Assertions.assertEquals(null, result);
    }

    private static class CSVRecord {
        private final String[] values;
        private final Map<String, Integer> mapping;

        public CSVRecord(final String[] values, final Map<String, Integer> mapping,
                         final String comment, final long recordNumber) {
            this.values = values;
            this.mapping = mapping;
        }

        public String get(final String name) {
            if (mapping == null) {
                throw new IllegalStateException(
                        "No header mapping was specified, the record values can't be accessed by name");
            }
            final Integer index = mapping.get(name);
            try {
                return index != null ? values[index.intValue()] : null;
            } catch (ArrayIndexOutOfBoundsException e) {
                throw new IllegalArgumentException(
                        String.format(
                                "Index for header '%s' is %d but CSVRecord only has %d values!",
                                name, index.intValue(), values.length));
            }
        }
    }
}