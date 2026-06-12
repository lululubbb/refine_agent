package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_3_5Test {

    @Test
    public void testGet_normalCase() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);
        String[] values = {"value1", "value2"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = record.get("header1");

        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_headerNotFound() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {"value1", "value2"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = record.get("header3");

        Assertions.assertEquals(null, result);
    }

    @Test
    public void testGet_noMapping() throws Exception {
        String[] values = {"value1", "value2"};
        CSVRecord record = new CSVRecord(values, null, null, 1);

        IllegalStateException thrown = Assertions.assertThrows(IllegalStateException.class, () -> {
            record.get("header1");
        });

        Assertions.assertEquals("No header mapping was specified, the record values can't be accessed by name", thrown.getMessage());
    }

    @Test
    public void testGet_indexOutOfBounds() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 5); // Intentionally out of bounds
        String[] values = {"value1", "value2"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        IllegalArgumentException thrown = Assertions.assertThrows(IllegalArgumentException.class, () -> {
            record.get("header1");
        });

        Assertions.assertEquals("Index for header 'header1' is 5 but CSVRecord only has 2 values!", thrown.getMessage());
    }

    @Test
    public void testGet_withReflection() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Method method = CSVRecord.class.getDeclaredMethod("get", String.class);
        method.setAccessible(true);
        String result = (String) method.invoke(record, "header1");

        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_withDifferentMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);
        mapping.put("header3", 2); // New mapping for a header not in the values
        String[] values = {"value1", "value2"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = record.get("header3");

        Assertions.assertEquals(null, result);
    }
}