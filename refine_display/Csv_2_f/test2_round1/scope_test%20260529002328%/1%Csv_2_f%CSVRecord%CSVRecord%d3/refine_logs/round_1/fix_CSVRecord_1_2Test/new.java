package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_1_2Test {

    @Test
    public void testCSVRecord_normalCase() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        String comment = "This is a comment";
        long recordNumber = 1L;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);

        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("This is a comment", record.getComment());
        Assertions.assertEquals(2, record.size());
        Assertions.assertEquals(1L, record.getRecordNumber());
    }

    @Test
    public void testCSVRecord_emptyValues() throws Exception {
        String[] values = null;
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "No values";
        long recordNumber = 2L;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);

        Assertions.assertEquals(0, record.size());
        Assertions.assertEquals("No values", record.getComment());
    }

    @Test
    public void testCSVRecord_withMapping() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        long recordNumber = 3L;

        CSVRecord record = new CSVRecord(values, mapping, null, recordNumber);

        Assertions.assertTrue(record.isMapped("column1"));
        Assertions.assertTrue(record.isMapped("column2"));
        Assertions.assertFalse(record.isMapped("column3"));
    }

    @Test
    public void testCSVRecord_isConsistent() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        long recordNumber = 4L;

        CSVRecord record = new CSVRecord(values, mapping, null, recordNumber);

        Assertions.assertTrue(record.isConsistent());
    }

    @Test
    public void testCSVRecord_isSet() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        long recordNumber = 5L;

        CSVRecord record = new CSVRecord(values, mapping, null, recordNumber);

        Assertions.assertTrue(record.isSet("column1"));
        Assertions.assertFalse(record.isSet("column3"));
    }

    @Test
    public void testCSVRecord_iterator() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        long recordNumber = 6L;

        CSVRecord record = new CSVRecord(values, mapping, null, recordNumber);
        Iterator<String> iterator = record.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testCSVRecord_toString() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        long recordNumber = 7L;

        CSVRecord record = new CSVRecord(values, mapping, null, recordNumber);
        String result = record.toString();

        String expected = "CSVRecord{" +
                "values=" + Arrays.toString(values) +
                ", comment=" + null +
                ", recordNumber=" + recordNumber +
                '}';
        
        Assertions.assertEquals(expected, result);
    }
}