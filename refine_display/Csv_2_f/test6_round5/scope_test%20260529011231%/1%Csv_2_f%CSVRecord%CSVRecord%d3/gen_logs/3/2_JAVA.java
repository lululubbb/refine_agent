package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_1_3Test {

    @Test
    public void testCSVRecord_normalCase() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        mapping.put("column3", 2);
        String comment = "This is a comment";
        long recordNumber = 1L;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);

        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
        Assertions.assertEquals("This is a comment", record.getComment());
        Assertions.assertEquals(3, record.size());
        Assertions.assertTrue(record.isMapped("column1"));
        Assertions.assertFalse(record.isMapped("column4"));
        Assertions.assertTrue(record.isSet("column1"));
        Assertions.assertFalse(record.isSet("column4"));
        Assertions.assertEquals(1L, record.getRecordNumber());
    }

    @Test
    public void testCSVRecord_emptyValues() throws Exception {
        String[] values = null;
        Map<String, Integer> mapping = Collections.emptyMap();
        String comment = null;
        long recordNumber = 2L;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);

        Assertions.assertEquals(0, record.size());
        Assertions.assertEquals(2L, record.getRecordNumber());
        Assertions.assertNull(record.getComment());
    }

    @Test
    public void testCSVRecord_withMapping() throws Exception {
        String[] values = {"valueA", "valueB"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("keyA", 0);
        mapping.put("keyB", 1);
        String comment = "Another comment";
        long recordNumber = 3L;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);

        Assertions.assertEquals("valueA", record.get("keyA"));
        Assertions.assertEquals("valueB", record.get("keyB"));
        Assertions.assertEquals("Another comment", record.getComment());
    }

    @Test
    public void testCSVRecord_invalidIndex() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "Valid comment";
        long recordNumber = 4L;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);

        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(2);
        });
    }

    @Test
    public void testCSVRecord_iterator() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "Comment";
        long recordNumber = 5L;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);

        int count = 0;
        for (String value : record) {
            Assertions.assertEquals(values[count], value);
            count++;
        }
        Assertions.assertEquals(values.length, count);
    }
}