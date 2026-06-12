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
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        String comment = "This is a comment";
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        Assertions.assertEquals("value1", csvRecord.get(0));
        Assertions.assertEquals("value2", csvRecord.get(1));
        Assertions.assertEquals("This is a comment", csvRecord.getComment());
        Assertions.assertEquals(1L, csvRecord.getRecordNumber());
        Assertions.assertEquals(2, csvRecord.size());
    }

    @Test
    public void testCSVRecord_emptyValues() throws Exception {
        String[] values = null;
        Map<String, Integer> mapping = Collections.emptyMap();
        String comment = null;
        long recordNumber = 2L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        Assertions.assertEquals(0, csvRecord.size());
        Assertions.assertEquals("", csvRecord.get(0)); // should return empty string
    }

    @Test
    public void testCSVRecord_withMapping() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        long recordNumber = 3L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, null, recordNumber);

        Assertions.assertTrue(csvRecord.isMapped("column1"));
        Assertions.assertFalse(csvRecord.isMapped("column3"));
    }

    @Test
    public void testCSVRecord_isConsistent() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        long recordNumber = 4L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, null, recordNumber);

        Assertions.assertTrue(csvRecord.isConsistent());
    }

    @Test
    public void testCSVRecord_getPrivateMethod() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        long recordNumber = 5L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, null, recordNumber);

        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        String[] result = (String[]) method.invoke(csvRecord);

        Assertions.assertArrayEquals(values, result);
    }
}