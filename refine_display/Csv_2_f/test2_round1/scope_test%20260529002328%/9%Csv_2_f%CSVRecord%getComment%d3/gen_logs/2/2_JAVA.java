package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;

public class CSVRecord_9_2Test {

    @Test
    public void testGetComment_normalCase() throws Exception {
        String[] values = {"value1", "value2"};
        HashMap<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment());
    }

    @Test
    public void testGetComment_emptyComment() throws Exception {
        String[] values = {"value1", "value2"};
        HashMap<String, Integer> mapping = new HashMap<>();
        String comment = "";
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment());
    }

    @Test
    public void testGetComment_nullComment() throws Exception {
        String[] values = {"value1", "value2"};
        HashMap<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertNull(record.getComment());
    }

    @Test
    public void testGetComment_withDifferentRecordNumbers() throws Exception {
        String[] values1 = {"value1", "value2"};
        HashMap<String, Integer> mapping1 = new HashMap<>();
        String comment1 = "First comment";
        long recordNumber1 = 1;

        CSVRecord record1 = new CSVRecord(values1, mapping1, comment1, recordNumber1);
        Assertions.assertEquals(comment1, record1.getComment());

        String[] values2 = {"value3", "value4"};
        HashMap<String, Integer> mapping2 = new HashMap<>();
        String comment2 = "Second comment";
        long recordNumber2 = 2;

        CSVRecord record2 = new CSVRecord(values2, mapping2, comment2, recordNumber2);
        Assertions.assertEquals(comment2, record2.getComment());
    }
}