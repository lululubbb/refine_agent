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

public class CSVRecord_1_2Test {

    @Test
    public void testCSVRecord_normalCase() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        CSVRecord record = new CSVRecord(values, mapping, "This is a comment", 1L);

        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
        Assertions.assertEquals("This is a comment", record.getComment());
        Assertions.assertEquals(1L, record.getRecordNumber());
        Assertions.assertEquals(3, record.size());
    }

    @Test
    public void testCSVRecord_emptyValues() throws Exception {
        String[] values = null;
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, "Comment", 2L);

        Assertions.assertEquals(0, record.size());
        Assertions.assertEquals("", record.get(0));
    }

    @Test
    public void testCSVRecord_noMapping() throws Exception {
        String[] values = {"value1", "value2"};
        CSVRecord record = new CSVRecord(values, null, "No mapping", 3L);

        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(2);
        });
    }

    @Test
    public void testCSVRecord_getByName() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        CSVRecord record = new CSVRecord(values, mapping, "Comment", 4L);

        Assertions.assertEquals("value1", record.get("col1"));
        Assertions.assertEquals("value2", record.get("col2"));
        Assertions.assertEquals("value3", record.get("col3"));
    }

    @Test
    public void testCSVRecord_getByName_notMapped() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, "Comment", 5L);

        Assertions.assertThrows(IllegalArgumentException.class, () -> {
            record.get("col3");
        });
    }

    @Test
    public void testCSVRecord_isConsistent() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 6L);

        Method method = CSVRecord.class.getDeclaredMethod("isConsistent");
        method.setAccessible(true);
        boolean result = (boolean) method.invoke(record);

        Assertions.assertTrue(result);
    }

    @Test
    public void testCSVRecord_isMapped() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        CSVRecord record = new CSVRecord(values, mapping, null, 7L);

        Assertions.assertTrue(record.isMapped("col1"));
        Assertions.assertFalse(record.isMapped("col2"));
    }

    @Test
    public void testCSVRecord_isSet() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        CSVRecord record = new CSVRecord(values, mapping, null, 8L);

        Assertions.assertTrue(record.isSet("col1"));
        Assertions.assertFalse(record.isSet("col2"));
    }

    @Test
    public void testCSVRecord_iterator() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(values, null, null, 9L);
        Iterator<String> iterator = record.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertEquals("value3", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testCSVRecord_toString() throws Exception {
        String[] values = {"value1", "value2"};
        CSVRecord record = new CSVRecord(values, null, "Comment", 10L);

        String result = record.toString();
        Assertions.assertTrue(result.contains("value1"));
        Assertions.assertTrue(result.contains("value2"));
        Assertions.assertTrue(result.contains("Comment"));
        Assertions.assertTrue(result.contains("10"));
    }
}