package org.apache.commons.csv;

import java.io.Serializable;
import java.lang.reflect.Method;
import java.util.Arrays;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

public class CSVRecord_1_4Test {

    @Test
    public void testCSVRecord_normalCase() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        String comment = "This is a comment";
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);

        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("This is a comment", record.getComment());
        Assertions.assertEquals(2, record.size());
        Assertions.assertEquals(1, record.getRecordNumber());
    }

    @Test
    public void testCSVRecord_emptyValues() throws Exception {
        String[] values = null;
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);

        Assertions.assertEquals(0, record.size());
        Assertions.assertEquals("This is a comment", record.getComment());
    }

    @Test
    public void testCSVRecord_isMapped() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, null, recordNumber);

        Assertions.assertTrue(record.isMapped("column1"));
        Assertions.assertTrue(record.isMapped("column2"));
        Assertions.assertFalse(record.isMapped("column3"));
    }

    @Test
    public void testCSVRecord_isSet() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, null, recordNumber);

        Assertions.assertTrue(record.isSet("column1"));
        Assertions.assertFalse(record.isSet("column2"));
    }

    @Test
    public void testCSVRecord_iterator() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, null, recordNumber);
        Iterator<String> iterator = record.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testCSVRecord_withDifferentValues() throws Exception {
        String[] values = {"", "value2", null};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        long recordNumber = 2;

        CSVRecord record = new CSVRecord(values, mapping, null, recordNumber);

        Assertions.assertEquals("", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertNull(record.get(2)); // Expecting null for the third value
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals(2, record.getRecordNumber());
    }

    private String invokePrivateGetMethod(CSVRecord record, int index) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("get", int.class);
        method.setAccessible(true);
        return (String) method.invoke(record, index);
    }
}