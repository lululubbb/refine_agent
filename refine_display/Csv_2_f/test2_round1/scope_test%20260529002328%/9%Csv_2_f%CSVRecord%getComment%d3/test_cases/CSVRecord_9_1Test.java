package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_9_1Test {

    @Test
    public void testGetComment_withValidComment() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long recordNumber = 1;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);
        String result = csvRecord.getComment();
        
        Assertions.assertEquals(comment, result);
    }

    @Test
    public void testGetComment_withNullComment() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long recordNumber = 1;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);
        String result = csvRecord.getComment();
        
        Assertions.assertNull(result);
    }

    @Test
    public void testGet_withValidIndex() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long recordNumber = 1;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);
        String result = csvRecord.get(0);
        
        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_withInvalidIndex() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long recordNumber = 1;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);
        
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            csvRecord.get(2);
        });
    }

    @Test
    public void testIsConsistent_withValidValues() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long recordNumber = 1;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);
        
        Assertions.assertTrue(csvRecord.isConsistent());
    }

    @Test
    public void testToString() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long recordNumber = 1;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);
        String result = csvRecord.toString();
        
        Assertions.assertEquals("CSVRecord{values=[value1, value2], comment='This is a comment', recordNumber=1}", result);
    }

    private CSVRecord createCSVRecord(String[] values, Map<String, Integer> mapping, String comment, long recordNumber) throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, comment, recordNumber);
    }
}