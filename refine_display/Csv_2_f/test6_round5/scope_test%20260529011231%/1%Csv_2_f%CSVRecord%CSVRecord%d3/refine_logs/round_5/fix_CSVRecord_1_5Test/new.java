package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_1_5Test {

    @Test
    public void testCSVRecord_normalCase() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        CSVRecord record = new CSVRecord(values, mapping, "This is a comment", 1);

        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
        Assertions.assertEquals("This is a comment", record.getComment());
        Assertions.assertEquals(1, record.getRecordNumber());
        Assertions.assertEquals(3, record.size());
    }

    @Test
    public void testCSVRecord_emptyValues() throws Exception {
        String[] values = null;
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, "No values", 2);

        Assertions.assertEquals(0, record.size());
        Assertions.assertEquals(0, record.values().length);
        Assertions.assertEquals(0, record.getRecordNumber());
    }

    @Test
    public void testCSVRecord_mappingCheck() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        CSVRecord record = new CSVRecord(values, mapping, null, 3);

        Assertions.assertTrue(record.isMapped("col1"));
        Assertions.assertFalse(record.isMapped("col2"));
        Assertions.assertEquals(1, record.size());
    }

    @Test
    public void testCSVRecord_isSet() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        CSVRecord record = new CSVRecord(values, mapping, null, 4);

        Assertions.assertTrue(record.isSet("col1"));
        Assertions.assertFalse(record.isSet("col2"));
        Assertions.assertEquals(2, record.size());
    }

    @Test
    public void testCSVRecord_consistency() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        CSVRecord record = new CSVRecord(values, mapping, null, 5);

        Assertions.assertTrue(record.isConsistent());
        Assertions.assertEquals(2, record.size());
    }

    @Test
    public void testCSVRecord_iterator() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 6);

        Iterator<String> iterator = record.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value3", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testCSVRecord_toString() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 7);

        Assertions.assertEquals("[value1, value2]", record.toString());
        Assertions.assertEquals(2, record.size());
    }
}